package clio.core.tables;

import clio.core.Dttms;
import clio.core.Strings;

import java.time.LocalDateTime;

public interface Row {

    default Object read(Column col) {
        return readString(col);
    }

    String readString(Column col);

    default int readInt(Column col) {
        return Strings.parse(readString(col), Integer.class) ;
    }

    default long readLong(Column col) {
        return Strings.parse(readString(col), Long.class);
    }

    default double readDouble(Column col) {
        return Double.parseDouble(readString(col));
    }

    default LocalDateTime readDttm(Column col) {
        return Dttms.parseDttm(readString(col));
    }
}
