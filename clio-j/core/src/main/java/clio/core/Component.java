package clio.core;

public interface Component {
    void start(Application app) throws Exception;

    default void prepareShutdown() throws Exception {}

    void stop() throws Exception;
}
