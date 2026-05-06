package clio.scheduler;

import clio.core.*;
import clio.core.router.UserException;
import clio.scheduler.tasks.*;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Consumer;

public class TaskScheduler {

    private static final Logger log = LogManager.getLogger(TaskScheduler.class);

    private final Map<String, ScheduledTask> tasks = new HashMap<>();

    private final Executor executor;
    private final Consumer<TaskStatus> statuses;
    private final Map<String, TaskStatus> lastStatuses = new ConcurrentHashMap<>();
    private final Clock clock;

    public TaskScheduler(Clock clock, Consumer<TaskStatus> statuses) {
        this.executor = new Executor(clock);
        this.clock = clock;
        this.statuses = statuses;
    }

    public Executor executor() {
        return executor;
    }

    public void schedule(List<Task> tasks, Map<?, TaskStatus> previous) {
        synchronized (this.tasks) {

            for (var task : this.tasks.values())
                task.close();

            this.tasks.clear();

            for (var task : tasks)
            {
                if (this.tasks.containsKey(task.name()))
                    throw new RuntimeException("Duplicate task: " + task.name());

                var st = new ScheduledTask(task, previous.get(task.name()), task.dependencies());
                this.tasks.put(task.name(), st);
                st.schedule();
            }

            for (var ts : previous.values()) {
                lastStatuses.put(ts.name(), ts);
            }
        }
    }

    public LocalDateTime runNow(String name, boolean force) {
        ScheduledTask task;
        synchronized (tasks) {
            task = this.tasks.get(name);;
        }
        return task.runNow(force);
    }

    class ScheduledTask implements Runnable, Executor.ExecutorCallback, Disposable {
        private final Task task;
        private final List<TaskDependency> dependencies;

        private boolean disposed = false;
        private boolean running = false;

        private LocalDateTime nextDttm = null;
        private LocalDateTime previousDttm = null;
        private TaskResultState previousResult = TaskResultState.Unknown;
        private String msg = "";

        ScheduledTask(Task task, TaskStatus previous, List<TaskDependency> dependencies) {
            this.task = task;
            this.dependencies = dependencies;

            if (previous != null) {
                previousResult = previous.previousResult();
                previousDttm = previous.dttm();
                msg = previous.msg();
            }
        }

        public void schedule() {
            LocalDateTime nextDttm = null;
            synchronized (this) {
                var now = clock.now();
                this.nextDttm = nextDttm = task.next(now);
                var state = nextDttm == null ? TaskState.Unscheduled : TaskState.Scheduled;
                this.update(now, state);
            }

            if (nextDttm != null) {
                log.info("Scheduled Task[{}] at {}", this.task.name(), nextDttm);
                executor.schedule(this.task.name() + " (schedule)", this::runOnSchedule, nextDttm);
            }
        }

        protected void update(LocalDateTime now, TaskState state) {
            var ts = new TaskStatus(now, task.name(), state, nextDttm, previousDttm, previousResult, msg);
            lastStatuses.put(task.name(), ts);
            statuses.accept(ts);
        }

        public LocalDateTime runNow(boolean force) {
            synchronized (this) {
                if (running)
                    throw new UserException("Task already running");

                if (disposed)
                    throw new UserException("Task disposed");

                nextDttm = LocalDateTime.now();
                runOnSchedule(force);
                return nextDttm;
            }
        }

        public void runOnSchedule() {
            runOnSchedule(false);
        }

        public void runOnSchedule(boolean force) {
            synchronized (this) {
                if (disposed)
                    return;

                if (running)
                    return;

                if (dependencies != null && !force) {
                    var now = clock.now();
                    var sod = Dttms.sod(now);

                    for (var d : dependencies) {
                        var ds = lastStatuses.get(d.name());
                        if (ds != null && (ds.previousDttm() == null || !ds.previousDttm().isAfter(sod))) {
                            // ignore results from yesterday
                            lastStatuses.remove(d.name());
                            ds = null;
                        }

                        if (ds == null || ds.previousResult() != TaskResultState.Success) {
                            handleNotReady(now, d.name(), d.retry());
                            return;
                        }
                    }
                }

                running = true;
                update(clock.now(), TaskState.Running);
            }
            executor.run(this.task.name() + " (runner)", this);
        }

        void handleNotReady(LocalDateTime now, String dependencyName, boolean retry) {
            // dependency has not run or has not succeeded
            if (retry) {
                // wait and retry
                log.info("Task[{}] waiting for dependency [{}]", task.name(), dependencyName);
                msg = "Waiting for [" + dependencyName + "]";
                nextDttm = nextDttm.plusMinutes(1);
                update(now, TaskState.Waiting);
                executor.schedule(task.name() + " (schedule)", this::runOnSchedule, nextDttm);
            } else {
                // bail
                log.info("Task[{}] cut due to dependency [{}]", this.task.name(), dependencyName);
                msg = "Dependency [" + dependencyName + "] not met";
                previousResult = TaskResultState.Problem;
                previousDttm = nextDttm;
                update(now, TaskState.Skipped);
            }
        }

        @Override
        public void close() {
            synchronized (this) {
                disposed = true;
            }
        }

        @Override
        public void run() {
            LocalDateTime dttm;
            synchronized (this) {
                dttm = nextDttm;
            }

            try {
                log.info("Running Task[{}]...", this.task.name());
                task.run(dttm);
            } finally {
                synchronized (this) {
                    running = false;
                }
            }
        }

        @Override
        public void onFinished(boolean success, Throwable err) {
            synchronized (this) {
                this.msg = success ? "" : Exceptions.cleanMessage(err);
                this.previousResult = success ? TaskResultState.Success : TaskResultState.Problem;
                this.previousDttm = nextDttm;
                log.info("Task[{}] finished {}", this.task.name(), success ? "successfully" : "unsuccessfully: " + msg);
            }

            this.schedule();
        }

        @Override
        public void notReady() {
            synchronized (this) {
                handleNotReady(LocalDateTime.now(), "self", true);
            }
        }
    }
}

