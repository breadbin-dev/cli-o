package clio.core.rest;

public class ConnectionException extends RuntimeException {

    public ConnectionException(String message) {
        super(message);
    }

    public ConnectionException(Throwable ex) {
        super(ex);
    }
}
