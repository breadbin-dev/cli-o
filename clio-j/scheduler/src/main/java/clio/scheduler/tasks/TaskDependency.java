package clio.scheduler.tasks;

public record TaskDependency (String name, boolean retry) {
}
