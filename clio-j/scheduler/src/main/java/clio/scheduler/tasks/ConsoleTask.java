package clio.scheduler.tasks;

import clio.core.ConsoleCommand;

import java.time.LocalDateTime;
import java.util.List;

public class ConsoleTask extends Task {
    private final String command;
    private final String logDir;

    public ConsoleTask(String name, String schedule, List<TaskDependency> dependencies, String command, String logDir) {
        super(name, schedule, dependencies);
        this.command = command;
        this.logDir = logDir;
    }

    public void run(LocalDateTime schedule) {
        var logName = name().replace(" ", "_") + ".log";
        var logFile = logDir + "/" + logName;
        ConsoleCommand.of(command, logFile, schedule, name()).run();
    }
}
