package clio.scheduler.tasks;

import clio.core.CountByKey;
import clio.core.Exceptions;
import clio.core.Strings;
import clio.core.router.RouterClient;
import clio.core.tables.Aggregation;
import clio.core.tables.ArrayTable;
import clio.core.tables.Table;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;

import static clio.core.Strings.f;

public class CheckTask extends Task {

    private static final Logger log = LogManager.getLogger(CheckTask.class);

    private final String command;
    private final String key;
    private final String keyPattern;
    private final String groupBy;
    private final Aggregation[] groupAggregation;
    private final String msg;

    private final int allowedRunFailures;
    private final int allowedCheckFailures;
    private final int maxTickets;

    private final RouterClient router;

    private int currentRunFailures;
    private final CountByKey<String> currentCheckFailures = new CountByKey<>();

    public CheckTask(String name, String schedule, List<TaskDependency> dependencies, String command, String keyPattern, String groupBy, String msg, RouterClient router, int allowedRunFailures, int allowedCheckFailures, int maxTickets) {
        super(name, schedule, dependencies);
        this.command = command;
        this.key = keyFromPattern(keyPattern);
        this.keyPattern = keyPattern;
        this.msg = msg;
        this.allowedRunFailures = allowedRunFailures;
        this.allowedCheckFailures = allowedCheckFailures;
        this.maxTickets = maxTickets;
        this.router = router;

        if (Strings.hasValue(groupBy)) {
            var args = groupBy.split(":");
            this.groupBy = args[0];
            this.groupAggregation = Aggregation.parseList(args[1]);
        } else {
            this.groupBy = null;
            this.groupAggregation = null;
        }
    }

    private static String keyFromPattern(String pattern) {
        var key = pattern.split(":")[0];
        assert !key.isEmpty();
        assert !key.startsWith("$");
        return key;
    }

    private Table toTable(Object rType, Object result) {
        Table table;
        if ("html".equals(rType))
            table = ArrayTable.fromHtml((String)result);
        else
            table = ArrayTable.fromJson(result);

        if (Strings.hasValue(groupBy))
            table = table.aggregateBy(groupBy, groupAggregation);

        return table;
    }


    @Override
    public void run(LocalDateTime schedule) {
        var args = new HashMap<String, Object>();
        var tickets = new HashMap<String, String>();
        args.put("tickets", tickets);
        args.put("key", this.key);

        try {
            var response = router.call(this.command);
            var rType = response.get("type");
            var result = response.get("result");
            if (("text".equals(rType) || "table".equals(rType)) && "[]".equals(result)) {
                args.put("mode", "diff");  // empty result
                currentCheckFailures.clear();
            } else if ("html".equals(rType) || "table".equals(rType)) {
                var table = toTable(rType, result);
                var prevFailedKeys = new HashSet<>(currentCheckFailures.keys());
                for (var row : table.rows()) {
                    var key = Strings.replaceVariables(keyPattern, s -> row.readString(table.column(s)));
                    var message = Strings.replaceVariables(msg, s -> row.readString(table.column(s)));
                    if (currentCheckFailures.increment(key) > allowedCheckFailures) {
                        tickets.put(key, message);
                    } else {
                        log.warn("ignored check within allowance: {}", key);
                    }
                    prevFailedKeys.remove(key);
                }
                currentCheckFailures.removeAll(prevFailedKeys);
                args.put("mode", "diff");
            } else {
                throw new RuntimeException(f("{}: {}", rType, result));
            }
            currentRunFailures = 0;

            var totalTickets = tickets.size();
            if (totalTickets >= maxTickets) {
                tickets.clear();
                tickets.put(key + ":_all_", f("[{}] raised {} tickets", this.name(), totalTickets));
            }


        } catch (Exception ex) {
            ++currentRunFailures;

            var msg = Exceptions.cleanMessage(ex, 100);
            if (currentRunFailures > allowedRunFailures) {
                tickets.put(key, f("Problem running [{}]: {}", this.name(), msg));
                args.put("mode", "add");
                log.warn("Problem running [{}|{}]: {}", this.name(), this.command, msg);
            } else {
                log.warn("ignored run within allowance [{}]: {}", key, msg);
                return;
            }
        }

        router.call("tickets.bulk", args);
    }
}
