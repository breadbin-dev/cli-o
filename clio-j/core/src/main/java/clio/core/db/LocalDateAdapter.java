package clio.core.db;

import java.sql.SQLException;
import java.time.LocalDate;

public class LocalDateAdapter extends JdbcAdapter<LocalDate> {
    public LocalDateAdapter() {
        super(LocalDate.class);
    }

    @Override
    public void insert(LocalDate obj, JdbcStatement stmt) throws SQLException {
        stmt.setDt(obj);
    }

    @Override
    public LocalDate select(JdbcResult result) throws SQLException {
        return result.getDt();
    }
}
