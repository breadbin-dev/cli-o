package clio.core.engine;

import java.util.Collection;
import java.util.LinkedList;
import java.util.List;

public class LinkedListInput<V> implements Input<V, List<V>> {

    private final LinkedList<V> in;
    private final LinkedList<V> out;

    public LinkedListInput() {
        this.in = new LinkedList<>();
        this.out = new LinkedList<>();
    }

    @Override
    public void in(long seq, V in) {
        this.in.add(in);
    }

    @Override
    public void inAll(long seq, Collection<V> in) {
        this.in.addAll(in);
    }

    @Override
    public List<V> tick() {
        out.addAll(in);
        in.clear();
        return out;
    }
}
