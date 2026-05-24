package clio.core;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

public class Executor {

    public static void safeSleep(long millis) {
        try {
            Thread.sleep(millis);
        } catch (InterruptedException ex) {
            // ok
        }
    }

    public interface ExecutorCallback {
        void onFinished(boolean success, Throwable err);
        void notReady();
    }

    private static final Logger log = LogManager.getLogger(Executor.class);

    private final Clock clock;

    private final ConcurrentHashMap<String, ScheduledExecutorService> executors = new ConcurrentHashMap<>();

    public Executor() {
        this(Clock.system());
    }

    public Executor(Clock clock) {
        this.clock = clock;
    }

    public Clock clock() {
        return clock;
    }

    public void run(String key, Runnable runnable) {
        this.run(key, runnable, null);
    }

    public void runWithFixedDelay(String key, Runnable runnable, long delay, TimeUnit unit) {
        var executor = executors.computeIfAbsent(key, this::getExecutor);
        executor.scheduleWithFixedDelay(runnable, 0, delay, unit);
    }

    public void run(String key, Runnable runnable, ExecutorCallback callback) {
        var executor = executors.computeIfAbsent(key, this::getExecutor);
        executor.execute(new RunnableWrapper(key, runnable, callback));
    }

    public Disposable schedule(String key, Runnable runnable, LocalDateTime dttm) {
        return this.schedule(key, runnable, dttm, null);
    }

    public Disposable schedule(String key, Runnable runnable, LocalDateTime dttm, ExecutorCallback callback) {
        var executor = executors.computeIfAbsent(key, this::getExecutor);
        var delay = ChronoUnit.MILLIS.between(clock.now(), dttm);
        runnable = new RunnableWrapper(key, runnable, callback);

        if (delay <= 0) {
            executor.execute(runnable);
            return Disposable.empty();
        }
        else {
            var future = executor.schedule(runnable, delay, TimeUnit.MILLISECONDS);
            return () -> future.cancel(true);
        }
    }

    protected ScheduledExecutorService getExecutor(String key) {
        return Executors.newSingleThreadScheduledExecutor(new NamedThreads(key));
    }

    static class RunnableWrapper implements Runnable {

        private final String key;
        private final Runnable runnable;
        private final Executor.ExecutorCallback callback;

        public RunnableWrapper(String key, Runnable runnable, Executor.ExecutorCallback callback) {
            this.key = key;
            this.runnable = runnable;
            if (callback == null && runnable instanceof ExecutorCallback)
                callback = (ExecutorCallback) runnable;
            this.callback = callback;
        }

        @Override
        public void run() {
            try {
                try {
                    this.runnable.run();
                    if (callback != null)
                        this.callback.onFinished(true, null);
                } catch (NotReady nr) {
                    if (callback != null)
                        this.callback.notReady();
                } catch (Throwable err) {
                    if (callback != null)
                        this.callback.onFinished(false, err);
                    else
                        throw err;
                }
            } catch (Throwable err) {
                log.error("Unhandled problem [{}]", key, err);
            }
        }
    }

    public static void safeAsyncPoll(String name, long pollMs, Runnable runnable) {
        var hook = new ShutdownHook();
        Executors.newSingleThreadExecutor(new NamedThreads(name)).execute(() ->
        {
            var ok = true;
            while (hook.running()) {
                try {
                    runnable.run();
                    if (!ok)
                        log.info("[{}] re-established", name);
                    ok = true;
                } catch (Exception e) {
                    if (ok && hook.running())
                        log.error("[{}]: {}", name, e.getMessage(), e);
                    ok = false;
                }
                Executor.safeSleep(pollMs);
            }
        });
    }
}

