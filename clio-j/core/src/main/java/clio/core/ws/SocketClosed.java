package clio.core.ws;

public class SocketClosed extends RuntimeException {
    public SocketClosed(String message) {
        super(message);
    }
}
