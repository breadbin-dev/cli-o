package clio.router;

import clio.core.Application;
import clio.core.Component;
import clio.core.UserAuth;
import clio.core.db.DBUserAuth;

public class CreateUser implements Component {

    @Override
    public void start(Application app) {
        var auth = app.ensureService(UserAuth.class);
        var user = auth.addUser("example_user", "example@hotmail.com", "***");

        System.out.println("Added user: " + user);
    }

    @Override
    public void stop() {

    }

    public static void main(String[] args) {
        var app = new Application(
                DBUserAuth.component(),
                new CreateUser()
        );
        app.run(false);
    }
}
