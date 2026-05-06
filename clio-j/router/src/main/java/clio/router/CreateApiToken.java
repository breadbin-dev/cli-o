package clio.router;

import clio.core.Application;
import clio.core.Component;
import clio.core.Strings;
import clio.router.adapters.UserTokenJdbcAdapter;

public class CreateApiToken implements Component {

    @Override
    public void start(Application app) {
        var db = app.getDatabase("audit_db", new UserTokenJdbcAdapter());
        var tokens = new TokenStoreDb(db);

        var token = "api-" + Strings.random(15);
        tokens.store(token, "svc_breadin_dev", "");

        System.out.println("Created API token: " + token);
    }

    @Override
    public void stop() {

    }

    public static void main(String[] args) {
        var app = new Application(new CreateApiToken());
        app.run(false);
    }

}
