package clio.scheduler.tasks;

import clio.core.Cron;

import java.time.LocalDateTime;
import java.util.List;

public abstract class Task {
    private final String name;
    private final Cron schedule;
    private final List<TaskDependency> dependencies;

    public Task(String name, String schedule, List<TaskDependency> dependencies) {
        this.name = name;
        this.schedule = Cron.of(schedule);
        this.dependencies = dependencies;
    }

    public String name() {
        return name;
    }

    public List<TaskDependency> dependencies() {
        return dependencies;
    }

    public abstract void run(LocalDateTime schedule);

    public LocalDateTime next(LocalDateTime now) {
        if (schedule == null)
            return null;

        return schedule.next(now);
    }
}
