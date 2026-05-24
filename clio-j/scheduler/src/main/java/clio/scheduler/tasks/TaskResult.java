package clio.scheduler.tasks;

import java.time.LocalDateTime;

public record TaskResult(LocalDateTime started, LocalDateTime finished, TaskResultState state, String msg) {

}
