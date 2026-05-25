package clio.core;

public interface UserAuth {

    interface User {
        String username();
        String email();
    }

    User lookup(String username);

    boolean auth(User user, String pwd);

    default User addUser(String username, String email, String password) {
        throw new RuntimeException("not implemented");
    }

    default User lookup(String username, String password) {
        var user = lookup(username);
        if (user == null)
            throw new RuntimeException("User not found [" + username + "]");

        if (auth(user, password))
            return user;
        else
            throw new RuntimeException("Authentication failed [" + username + "]");
    }

    static UserAuth allowAll() {
        return new UserAuth() {

            @Override
            public User lookup(String username) {
                return new User() {
                    @Override
                    public String username() {
                        return username;
                    }

                    @Override
                    public String email() {
                        return username + "@allowall.com";
                    }
                };
            }

            @Override
            public boolean auth(User user, String pwd) {
                return true;
            }
        };
    }
}

