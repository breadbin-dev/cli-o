package clio.core.components;

import clio.core.Application;
import clio.core.Component;
import clio.core.adapters.ServiceStatusJdbcAdapter;

public class ServiceComponent implements Component {

    private final String serviceName;

    private ServiceMonitor monitor;

    public ServiceComponent(String serviceName) {
        this.serviceName = serviceName;
    }

    @Override
    public void start(Application app) {

        monitor = new ServiceMonitor(
                serviceName,
                app.getDatabase("audit_db", new ServiceStatusJdbcAdapter())
        );
        app.addService(monitor);
    }

    @Override
    public void prepareShutdown() {
        if (monitor != null)
            monitor.shutdown();
    }

    @Override
    public void stop() {
    }
}
