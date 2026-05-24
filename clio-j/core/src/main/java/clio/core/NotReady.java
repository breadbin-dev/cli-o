package clio.core;

public class NotReady extends RuntimeException {
    public NotReady(String message) {
        super(message);
    }
}
