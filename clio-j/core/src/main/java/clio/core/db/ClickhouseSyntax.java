package clio.core.db;

import clio.core.Dttms;

import java.time.LocalDate;
import java.time.LocalDateTime;

public class ClickhouseSyntax implements Syntax {

    @Override
    public String typeForField(Class<?> cls) {
        if (cls == LocalDate.class)
            return "Date";
        if (cls == LocalDateTime.class)
            return "DateTime64(9)";
        return Syntax.super.typeForField(cls);
    }

    @Override
    public String formatDttm(LocalDateTime dttm) {
        return "toDateTime64('" + Dttms.formatSql(dttm) + "', 9)";
    }
}
