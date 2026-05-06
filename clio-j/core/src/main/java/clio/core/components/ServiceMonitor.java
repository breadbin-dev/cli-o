package clio.core.components;

import clio.core.Component;
import clio.core.Exceptions;
import clio.core.NamedThreads;
import clio.core.ServiceStatus;
import clio.core.db.Database;

import java.time.LocalDateTime;
import java.util.concurrent.*;
import java.time.Duration;

public class ServiceMonitor {

    public static Component component(String serviceName) {
        return new ServiceComponent(serviceName);
    }

    private static final long minPeriod = 30;

    private final Database db;

    private volatile boolean running = true;
    private ServiceStatus lastStatus;
    private LocalDateTime lastReportTime;

    public ServiceMonitor(String serviceName, Database db) {
        lastStatus = new ServiceStatus(LocalDateTime.now(), serviceName, true, false, "");
        this.db = db;
        this.lastReportTime = LocalDateTime.now().minusSeconds(minPeriod);
    }

    public boolean running() {
        return running;
    }

    public void report(boolean connected, String message) {
        synchronized (this) {
            if (!running)
                return;

            LocalDateTime now = LocalDateTime.now();
            if (Duration.between(lastReportTime, now).getSeconds() < minPeriod && lastStatus.connected() == connected)
                return;

            lastReportTime = now;
            report(lastStatus = lastStatus.update(connected, message));
        }
    }

    private void report(ServiceStatus status) {
        db.write(status);
    }

    void shutdown() {
        synchronized (this) {
            running = false;

            report(lastStatus = lastStatus.shutdown());
        }
    }

    public void keepAlive(Executor executor) {
        var scheduler = Executors.newSingleThreadScheduledExecutor(new NamedThreads("Service Monitor"));
        var task = new KeepAliveTask(executor, scheduler);
        executor.execute(task);
    }

    public void pollingReport(Runnable reporter) {
        var scheduler = Executors.newSingleThreadScheduledExecutor(new NamedThreads("Service Monitor"));
        scheduler.scheduleWithFixedDelay(() -> {
            if (this.running()) {
                try {
                    reporter.run();
                } catch (Exception ex) {
                    report(false, Exceptions.msg(ex));
                }
            }
        }, 5, 15, TimeUnit.SECONDS);
    }

    class KeepAliveTask implements Runnable {

        private final Executor executor;
        private final ScheduledExecutorService scheduler;

        KeepAliveTask(Executor executor, ScheduledExecutorService scheduler) {
            this.executor = executor;
            this.scheduler = scheduler;
        }

        @Override
        public void run() {
            report(true, "");
            schedule();
        }

        public void schedule() {
            scheduler.schedule(() -> executor.execute(this), 30, TimeUnit.SECONDS);
        }
    }
}
