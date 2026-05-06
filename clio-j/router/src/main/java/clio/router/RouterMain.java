package clio.router;

import io.undertow.Undertow;
import clio.core.Application;
import clio.core.Component;
import clio.core.Ldap;
import clio.core.components.LdapComponent;
import clio.core.components.ServiceMonitor;
import clio.router.adapters.UserTokenJdbcAdapter;
import clio.router.entitlements.Entitlements;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

public class RouterMain implements Component {
    private static final Logger log = LogManager.getLogger(RouterMain.class);

    private Undertow server;

    @Override
    public void start(Application app) {

        var ldap = app.ensureService(Ldap.class);
        var entitlements = new Entitlements(Application.class.getClassLoader().getResourceAsStream("entitlements.json"));

        TokenStore tokens;
        if (app.isAuthDisabled()){
            tokens = new TokenStoreAllowAll();
        } else{
            var db = app.getDatabase("audit_db", new UserTokenJdbcAdapter());
            tokens = new TokenStoreDb(db);
        }

        var handlers = new Handlers(tokens);
        handlers.addHandler("login", new LoginHandler(tokens, ldap));
        var functions = new QueueHandler(entitlements);
        for (var root : functions.roots())
            handlers.addHandler(root, functions);

        var host = app.getProperty("router_host", "0.0.0.0");
        var port = Integer.parseInt(app.ensureProperty("router_port"));

        server = Undertow.builder().addHttpListener(port, host).setHandler(handlers).build();
        server.start();
        log.info("started Router on [{}:{}]", host, port);

        if (!app.isAuthDisabled()) {
            var monitor = app.ensureService(ServiceMonitor.class);
            monitor.keepAlive(handlers.executor());
        }
    }

    @Override
    public void stop() {
        server.stop();
    }

    public static void main(String[] args) {
        var app = new Application(new LdapComponent());
        if (!app.isAuthDisabled())
            app.addComponents(ServiceMonitor.component("router"), new RouterMain());
        else
            app.addComponents(new RouterMain());
        app.run();
    }
}