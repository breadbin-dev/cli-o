package clio.scheduler.tasks;

import clio.core.Keyed;

import java.time.LocalDateTime;
import java.util.List;

public record TaskStatus(LocalDateTime dttm, String name, TaskState state, LocalDateTime nextDttm, LocalDateTime previousDttm, TaskResultState previousResult, String msg) implements Keyed {
    public static List<String> keys() {
        return List.of("name");
    }

    public static List<String> nullable() {
        return List.of("nextDttm", "previousDttm", "previousResult", "msg");
    }

    @Override
    public Object key() {
        return name;
    }
}
