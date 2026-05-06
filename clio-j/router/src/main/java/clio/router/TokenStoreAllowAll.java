package clio.router;

import java.time.LocalDateTime;
import java.util.concurrent.ConcurrentHashMap;
import java.util.Map;

public class TokenStoreAllowAll implements TokenStore {

    private final Map<String, UserToken> tokens;

    public TokenStoreAllowAll() {
        this.tokens = new ConcurrentHashMap<>();
        var defaultUserToken = new UserToken(
                LocalDateTime.now(),
                "dev-token",
                System.getProperty("user.name"),
                "dev@allowall.com"
        );
        tokens.put("dev-token", defaultUserToken);
    }

    @Override
    public void store(String token, String username, String email) {
        UserToken userToken = new UserToken(LocalDateTime.now(), token, username, email);
        tokens.put(token, userToken);
    }

    @Override
    public UserToken retrieve(String token) {
        return tokens.get(token);
    }
}