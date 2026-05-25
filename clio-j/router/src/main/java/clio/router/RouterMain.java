package clio.router;

import clio.core.db.DBUserAuth;
import io.undertow.Undertow;
import clio.core.Application;
import clio.core.Component;
import clio.core.UserAuth;
import clio.core.ldap.LdapComponent;
import clio.router.entitlements.Entitlements;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

public class RouterMain implements Component {
    private static final Logger log = LogManager.getLogger(RouterMain.class);

    private Undertow server;

    @Override
    public void start(Application app) {

        var auth = app.ensureService(UserAuth.class);
        var entitlements = new Entitlements(Application.class.getClassLoader().getResourceAsStream("entitlements.json"));
        var tokens = app.ensureService(TokenStore.class);

        var handlers = new Handlers(tokens);
        handlers.addHandler("login", new LoginHandler(tokens, auth));
        var functions = new QueueHandler(entitlements);
        for (var root : functions.roots())
            handlers.addHandler(root, functions);

        var host = app.getProperty("router_host", "0.0.0.0");
        var port = Integer.parseInt(app.ensureProperty("router_port"));

        server = Undertow.builder().addHttpListener(port, host).setHandler(handlers).build();
        server.start();
        log.info("started Router on [{}:{}]", host, port);
    }

    @Override
    public void stop() {
        server.stop();
    }

    public static void main(String[] args) {

        var app = new Application(
                new RouterMain()
        );
        var auth = app.ensureProperty("auth_type");
        switch (auth) {
            case "disabled" -> {
                app.addService(UserAuth.allowAll(), UserAuth.class);
                app.addService(new TokenStoreAllowAll(), TokenStore.class);
            }
            case "ldap" -> {
                app.addComponent(0, new LdapComponent());
                app.addComponent(1, TokenStoreDb.component());
            }
            case "db" -> {
                app.addComponent(0, DBUserAuth.component());
                app.addComponent(1, TokenStoreDb.component());
            }
            default -> throw new RuntimeException("Unknown auth_type: " + auth);
        }

        app.run();
    }
}