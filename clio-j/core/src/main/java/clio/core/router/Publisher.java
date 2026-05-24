package clio.core.router;

import java.util.Map;

public class Publisher {
    private final RouterClient client;
    private final String function;
    private final String type;
    private final int refreshMs;

    protected boolean first = true;

    Publisher(RouterClient client, String function, String type, int refreshMs) {
        this.client = client;
        this.function = function;
        this.type = type;
        this.refreshMs = refreshMs;
    }

    public String publish(Map<String, ?> updates) {
        var full = first;
        first = false;
        return client.publish(function, type, updates, refreshMs, full);
    }
}
