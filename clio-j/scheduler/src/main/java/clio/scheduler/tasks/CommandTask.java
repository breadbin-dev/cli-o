package clio.scheduler.tasks;

import clio.core.router.RouterClient;

import java.time.LocalDateTime;
import java.util.List;


public class CommandTask extends Task {

    private final String command;
    private final RouterClient router;

    public CommandTask(String name, String schedule, List<TaskDependency> dependencies, String command, RouterClient router) {
        super(name, schedule, dependencies);
        this.command = command;
        this.router = router;
    }

    @Override
    public void run(LocalDateTime schedule) {
        router.call(this.command);
    }
}
