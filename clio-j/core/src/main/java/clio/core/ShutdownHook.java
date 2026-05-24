package clio.core;

import java.util.ArrayList;
import java.util.List;

public class ShutdownHook {

    private boolean running = true;

    private final List<Runnable> runners = new ArrayList<>();

    public ShutdownHook() {
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            synchronized (this) {
                running = false;
                this.notifyAll();
            }
            for (Runnable r : runners)
                r.run();
        }));
    }

    public void await(Runnable runner) {
        try {
            synchronized (this) {
                runners.add(runner);
                while (running)
                    this.wait();
            }
        } catch (InterruptedException ex) {
            // fine
        }
    }

    public boolean running() {
        synchronized (this) {
            return running;
        }
    }
}
