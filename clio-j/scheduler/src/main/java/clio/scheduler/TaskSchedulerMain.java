package clio.scheduler;

import com.fasterxml.jackson.core.type.TypeReference;
import clio.core.*;
import clio.core.components.ServiceMonitor;
import clio.core.router.RouterClient;
import clio.core.router.RouterHostComponent;
import clio.scheduler.adapters.TaskStatusJdbcAdapter;
import clio.scheduler.tasks.*;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;

public class  TaskSchedulerMain implements Component {

    @Override
    public void start(Application app) {
        var logsDir = app.ensureProperty("tasks_logsdir");
        var db = app.getDatabase("audit_db", new TaskStatusJdbcAdapter());
        var rc = app.getRouterClient();

        List<TaskDfn> tasks = new ArrayList<>();
        for (String c : app.getProperties("tasks_config_.*").values())
            tasks.addAll(Strings.readJsonFile(c, new TypeReference<List<TaskDfn>>(){}));
        var scheduler = new TaskScheduler(Clock.system(), db::write);

        tasks = Collections.filter(tasks, t ->
                Boolean.parseBoolean(t.enabled()) || app.env().equals(t.enabled())
        );

        app.addService(scheduler);

        var now = LocalDateTime.now();
        var lookback = Dttms.sod(now, -2);

        var lastStatus = new HashMap<Object, TaskStatus>();
        for (var task : db.select("select distinct on (name) * from task_status", TaskStatus.class, lookback, now, "order by dttm desc"))
            lastStatus.put(task.key(), task);

        var env = app.env();
        scheduler.schedule(Collections.map(tasks, t -> fromTaskDfn(t, logsDir, rc, env)), lastStatus);
    }


    private Task fromTaskDfn(TaskDfn t, String logsDir, RouterClient routerClient, String env) {
        var task = t.task();

        if (task.containsKey("script"))
            return new ConsoleTask(t.name(), t.schedule(), t.dependencies(), task.get("script"), logsDir);

        if (task.containsKey("check")) {
            var allowedRunFailures = Integer.parseInt(task.getOrDefault("allowedRunFailures", "1"));
            var allowedCheckFailures = Integer.parseInt(task.getOrDefault("allowedCheckFailures", "0"));
            var maxTickets = Integer.parseInt(task.getOrDefault("maxTickets", "5"));
            return new CheckTask(
                    t.name(),
                    t.schedule(),
                    t.dependencies(),
                    task.get("check"),
                    env + "|" + task.get("key"),
                    task.get("groupBy"),
                    task.get("message"),
                    routerClient,
                    allowedRunFailures,
                    allowedCheckFailures,
                    maxTickets
            );
        }
        if (task.containsKey("command"))
            return new CommandTask(t.name(), t.schedule(), t.dependencies(), task.get("command"), routerClient);

        throw new RuntimeException("Unable to create task: "+ task);
    }

    @Override
    public void stop() {

    }

    public static void main(String[] args) {
        var app = new Application(
                ServiceMonitor.component("scheduler"),
                new RouterHostComponent("_tasks", "tasks", "Tasks service commands"),
                new TaskSchedulerMain(),
                new TaskSchedulerWidget()
        );
        app.run();
    }
}