package clio.core;

public class SimpleReference<T> {

    private final boolean singular;

    private T value;
    private boolean isSet;

    public SimpleReference() {
        this(false);
    }

    public SimpleReference(boolean singular) {
        this.singular = singular;
    }

    public T set(T value) {
        if (this.singular && this.isSet)
            throw new RuntimeException("Already set");

        var prev = this.value;
        this.value = value;
        this.isSet = true;
        return prev;
    }

    public T get() {
        return this.value;
    }

    public boolean isSet() {
        return this.isSet;
    }
}
