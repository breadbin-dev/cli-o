package clio.router;

import clio.core.Exceptions;
import clio.core.Ldap;
import clio.core.Strings;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

public class LoginHandler implements Handler {

    private static final Logger log = LogManager.getLogger(LogManager.class);

    private final TokenStore tokens;
    private final Ldap ldap;

    public LoginHandler(TokenStore tokens, Ldap ldap) {
        this.tokens = tokens;
        this.ldap = ldap;
    }

    @Override
    public boolean doAuth() {
        return false;
    }

    @Override
    public void handle(String[] path, Request req) {
        var text = req.textAsMap();
        var username = text.get("username");
        var password = text.get("password");

        try {
            var user = ldap.lookupAuthUser(username, password);
            if (user != null) {
                var token = "user-" + Strings.random(15);
                tokens.store(token, username, user.email());
                req.sendText(token);
                log.info("login [{}] accepted: {}", username, token);
            } else {
                log.warn("login [{}] rejected", username);
                req.sendUnauthorized("login rejected");
            }
        } catch (Exception ex) {
            log.warn("problem on login: {}", Exceptions.msg(ex));
            req.sendUnauthorized("login failed");
        }
    }
}
