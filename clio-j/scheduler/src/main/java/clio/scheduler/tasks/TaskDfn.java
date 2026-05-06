package clio.scheduler.tasks;


import java.util.List;
import java.util.Map;

public record TaskDfn(String name, String schedule, Map<String, String> task, String enabled, List<TaskDependency> dependencies) {
}
