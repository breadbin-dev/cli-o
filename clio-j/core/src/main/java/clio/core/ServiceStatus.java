package clio.core;

import java.time.LocalDateTime;
import java.util.List;

public record ServiceStatus (LocalDateTime dttm, String name, boolean running, boolean connected, String msg) implements Keyed {
    public static List<String> keys() {
        return List.of("name");
    }

    public static List<String> nullable() {
        return List.of("msg");
    }

    @Override
    public Object key() {
        return name;
    }

    public ServiceStatus shutdown() {
        return new ServiceStatus(LocalDateTime.now(), name, false, connected, msg);
    }

    public ServiceStatus update(boolean connected, String msg) {
        return new ServiceStatus(LocalDateTime.now(), name, running, connected, msg);
    }
}
