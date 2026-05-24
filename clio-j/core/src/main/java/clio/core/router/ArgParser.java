package clio.core.router;

public interface ArgParser<T> {
    T parse(String args);
}
