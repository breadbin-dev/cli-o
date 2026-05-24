package clio.core.rest;

public class DeserializationException extends RuntimeException {
    public DeserializationException(Throwable ex) {
        super(ex);
    }
}
