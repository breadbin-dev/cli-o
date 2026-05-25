package clio.router;

import clio.core.Application;
import clio.core.Component;
import clio.core.db.Database;
import clio.router.adapters.UserTokenJdbcAdapter;

import java.time.LocalDateTime;
import java.util.concurrent.ConcurrentHashMap;

public class TokenStoreDb implements TokenStore {

    public static Component component() {
        return new Component() {
            @Override
            public void start(Application app) {
                var db = app.getDatabase("user_db", new UserTokenJdbcAdapter());
                app.addService(new TokenStoreDb(db), TokenStore.class);
            }

            @Override
            public void stop() {

            }
        };
    }

    private final ConcurrentHashMap<String, UserToken> tokens = new ConcurrentHashMap<>();
    private final Database db;

    public TokenStoreDb(Database db) {
        this.db = db;

        var lookback = LocalDateTime.now().minusMonths(3);

        for (var ut : db.select("select * from {table} where token like 'user-%'",
                UserToken.class,
                lookback, null)) {
            tokens.put(ut.token(), ut);
        }

        for (var ut : db.select("select * from {table} where token like 'api-%'",
                UserToken.class)) {
            tokens.put(ut.token(), ut);
        }
    }

    @Override
    public void store(String token, String username, String email) {
        var ut = new UserToken(LocalDateTime.now(), token, username, email);
        tokens.put(token, ut);
        db.write(ut);
    }

    @Override
    public UserToken retrieve(String token) {
        if (token == null) {
            return null;
        }
        return tokens.get(token);
    }
}