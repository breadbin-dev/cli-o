package clio.core.engine;

import java.util.Collection;

public interface Input<Tin, Tout> {
    void in(long seq, Tin in);

    default void inAll(long seq, Collection<Tin> in) {
        for (var i : in)
            in(seq, i);
    }

    Tout tick();
}
