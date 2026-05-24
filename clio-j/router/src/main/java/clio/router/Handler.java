package clio.router;

public interface Handler {
    void handle(String[] path, Request req);

    default boolean doAuth() {
        return true;
    }
}
