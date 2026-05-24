package clio.core.rest;

import clio.core.Exceptions;
import clio.core.Executor;
import clio.core.components.ServiceMonitor;
import org.slf4j.Logger;


public abstract class EventLoop {

    private final ServiceMonitor monitor;
    private final Logger log;
    protected final long sleep;

    public EventLoop(ServiceMonitor monitor, Logger log) {
        this(monitor, log, 0);
    }

    public EventLoop(ServiceMonitor monitor, Logger log, long sleep) {
        this.monitor = monitor;
        this.log = log;
        this.sleep = sleep;
    }

    protected abstract void poll();

    public void run() {
        run(null);
    }

    protected long sleep() {
        return sleep;
    }

    public void run(ServiceMonitor report) {
        var connected = true;
        while (monitor.running()) {
            try {
                poll();
                if (!connected) {
                    log.info("Reconnected");
                    connected = true;
                }

                if (report != null)
                    report.report(true, "");

                var sleep = sleep();
                if (sleep > 0)
                    Executor.safeSleep(sleep);

            } catch(ConnectionException ex) {
                if (connected) {
                    log.warn("Disconnected");
                    connected = false;
                }
                if (report != null)
                    report.report(false, Exceptions.msg(ex));

                log.debug("Disconnected or problem", ex);
                Executor.safeSleep(15000);
            }
        }
    }
}
