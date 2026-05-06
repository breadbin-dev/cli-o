package clio.core.engine;

public class LastInput<V> implements Input<V, V> {

    private V in;

    @Override
    public void in(long seq, V in) {
        this.in = in;
    }

    @Override
    public V tick() {
        return in;
    }
}
