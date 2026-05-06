package clio.core;

import clio.core.Executor;

import java.util.LinkedList;
import java.util.Queue;
import java.util.concurrent.*;

public class MockExecutor extends Executor {

    public final Queue<Runnable> tasks = new LinkedList<>();

    @Override
    public void run(String key, Runnable runnable, ExecutorCallback callback) {
        tasks.add(runnable);
    }

    @Override
    protected ScheduledExecutorService getExecutor(String key) {
        throw new RuntimeException("run/schedule methods should be mocked so this isn't called");
    }
}
