package clio.core;

import java.util.concurrent.ThreadFactory;
import java.util.concurrent.atomic.AtomicInteger;

import static clio.core.Strings.f;

public class NamedThreads implements ThreadFactory {

    private final String name;
    private final AtomicInteger counter;
    private final boolean daemon;

    public NamedThreads(String name) {
        this(name, true);
    }

    public NamedThreads(String name, boolean daemon) {
        this.name = name;
        this.daemon = daemon;
        this.counter = new AtomicInteger();
    }

    @Override
    public Thread newThread(Runnable r) {
        var t = new Thread(r, f("{}-{}", name, counter.incrementAndGet()));
        t.setDaemon(daemon);
        return t;
    }
}
