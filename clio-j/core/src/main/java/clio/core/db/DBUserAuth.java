package clio.core.db;

import clio.core.*;

import java.util.List;

import static clio.core.Strings.f;

public class DBUserAuth implements UserAuth {

    public static Component component() {
        return new Component() {
            @Override
            public void start(Application app) {
                var db = app.getDatabase("user_db", new AuthUserAdapter());
                var crypter = new Encrypter(app.ensureProperty("password_secret"));
                app.addService(new DBUserAuth(db, crypter), UserAuth.class);
            }

            @Override
            public void stop() {

            }
        };
    }

    public static class DBUser implements User, Keyed {
        private final String username;
        private final String email;
        private final String passhash;

        public DBUser(String username, String email, String passhash) {
            this.username = username;
            this.email = email;
            this.passhash = passhash;
        }

        public static List<String> keys() {
            return List.of("username");
        }

        @Override
        public Object key() {
            return username();
        }

        @Override
        public String username() {
            return username;
        }

        @Override
        public String email() {
            return email;
        }

        public String passhash() {
            return passhash;
        }

        @Override
        public String toString() {
            return f("DBUser[{}]", username);
        }
    }

    private final Database db;
    private final Encrypter crypter;

    public DBUserAuth(Database db, Encrypter crypter) {
        this.db = db;
        this.crypter = crypter;
    }

    @Override
    public User lookup(String username) {
        return db.selectSingle(f("select * from user where username = '{}'", username), DBUser.class);
    }

    @Override
    public boolean auth(User user, String pwd) {
        return crypter.authenticate(user.username(), pwd, getPwdHash(user.username()));
    }

    private String getPwdHash(String user) {
        return db.ensureSingle(f("select passhash from user where username = '{}'", user), String.class);
    }

    @Override
    public User addUser(String username, String email, String password) {
        var hash = crypter.hash(username, password);
        db.write(new DBUser(username, email, hash));
        return lookup(username);
    }
}
