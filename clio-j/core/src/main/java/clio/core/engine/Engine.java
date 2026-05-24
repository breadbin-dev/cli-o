package clio.core.engine;

import clio.core.Executor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.LocalDateTime;
import java.util.Collection;
import java.util.Map;


public abstract class Engine<T> {

    private static final Logger log = LoggerFactory.getLogger(Engine.class);

    protected final Executor executor;
    private final String execKey;

    private long seq = 0;
    private boolean scheduled = false;

    private boolean suspended = false;

    public Engine(Executor executor, String execKey) {
        this.executor = executor;
        this.execKey = execKey;
    }

    public void schedule(LocalDateTime dttm) {
        this.executor.schedule(execKey, this::doRun, dttm);
    }

    public void suspend(boolean suspended) {
        synchronized (this) {
            this.suspended = suspended;
        }
    }

    public void run() {
        synchronized (this) {
            if (scheduled || suspended)
                return;

            scheduled = true;
        }

        this.executor.run(execKey, this::doRun);
    }

    protected <Tin> void input(Tin in, Input<Tin, ?> input, boolean run) {
        synchronized (this) {
            var seq = ++this.seq;
            input.in(seq, in);

            if (run)
                this.run();
        }
    }

    protected <Tk, Tv> void input(Tk key, Tv value, MapInput<Tk, Tv, ?> input, boolean run) {
        synchronized (this) {
            var seq = ++this.seq;
            input.in(seq, key, value);

            if (run)
                this.run();
        }
    }

    protected <Tin> void inputs(Collection<Tin> in, Input<Tin, ?> input, boolean run) {
        synchronized (this) {
            var seq = ++this.seq;
            input.inAll(seq, in);

            if (run)
                this.run();
        }
    }

    protected <Tk, Tv> void inputs(Map<Tk, Tv> in, MapInput<Tk, Tv, ?> input, boolean run) {
        synchronized (this) {
            var seq = ++this.seq;
            input.inAll(seq, in);

            if (run)
                this.run();
        }
    }

    protected void unhandledException(Throwable ex) {
        suspended = true;
        log.error("Unhandled problem", ex);
        System.exit(1);
    }

    protected void doRun() {
        try {

            T tick;
            long seq;

            synchronized (this) {
                seq = ++this.seq;
                tick = this.tick(seq);
                scheduled = false;
            }
            execute(seq, tick);

        } catch (Throwable ex) {
            synchronized (this) {
                unhandledException(ex);
            }
        }
    }

    protected abstract T tick(long seq);

    protected abstract void execute(long seq, T tick);
}
