package clio.core.router;

import clio.core.Application;
import clio.core.Component;

public class RouterHostComponent implements Component {

    private final String queue;
    private final String functionRoot;
    private final String description;

    private RouterHost host;

    public RouterHostComponent(String queue, String functionRoot, String description) {
        this.queue = queue;
        this.functionRoot = functionRoot;
        this.description = description;
    }

    @Override
    public void start(Application app) {
        host = new RouterHost(
                app.ensureProperty("router_url"),
                app.ensureProperty("router_token"),
                queue,
                functionRoot,
                description
        );
        app.addService(host);
    }

    @Override
    public void stop() {
        if (host != null)
            host.close();
    }
}
