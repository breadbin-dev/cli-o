package clio.router;
import clio.core.Keyed;

import java.time.LocalDateTime;
import java.util.List;


public interface TokenStore {

    /**
     * Holds token information for users.
     */
    record UserToken(LocalDateTime dttm, String token, String username, String email) implements Keyed {
        public static List<String> keys() {
            return List.of("username");
        }

        @Override
        public Object key() {
            return username;
        }
    }

    /**
     * Stores the user token information (token, username, email).
     */
    void store(String token, String username, String email);

    /**
     * Retrieves the user token by its token string.
     */
    UserToken retrieve(String token);
}