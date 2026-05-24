package clio.scheduler;

import clio.core.Application;
import clio.core.Component;
import clio.core.Dttms;
import clio.core.Subscription;
import clio.core.components.ServiceMonitor;
import clio.core.router.CliArgParser;
import clio.core.router.RouterHost;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.concurrent.TimeUnit;

public class TaskSchedulerWidget implements Component {

    private static final Logger log = LoggerFactory.getLogger(TaskSchedulerWidget.class);

    private TaskScheduler scheduler;

    @Override
    public void start(Application app) {
        scheduler = app.ensureService(TaskScheduler.class);

        var host = app.ensureService(RouterHost.class);
        host.add("run", "run a specific task", Subscription.withLog(this::runTask, log, true),
                new CliArgParser.Option("t", "task", "str", "task name", false),
                new CliArgParser.Option("f", "force", "boolean", "force task (ignore dependencies)", false)
        );
        host.listenAsync();

        var monitor = app.ensureService(ServiceMonitor.class);
        scheduler.executor().runWithFixedDelay("_monitor", () -> monitor.report(host.isConnected(), ""), 30, TimeUnit.SECONDS);
    }

    public void runTask(String function, RouterHost.Call<?> call) {
        String task = call.ensureArg("task");
        log.info("User [{}] requested [{}] now", call.user(), task);

        call.respondText(Dttms.formatDttm(scheduler.runNow(task, call.getArg("force"))));
    }

    @Override
    public void stop() {

    }
}
