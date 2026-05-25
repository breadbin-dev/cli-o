package clio.router.adapters;

import clio.core.db.JdbcAdapter;
import clio.core.db.JdbcResult;
import clio.core.db.JdbcStatement;
import clio.router.TokenStore;

import java.sql.SQLException;

public class UserTokenJdbcAdapter extends JdbcAdapter<TokenStore.UserToken> {

    public UserTokenJdbcAdapter() {
        super(TokenStore.UserToken.class);
    }

    @Override
    public void insert(TokenStore.UserToken obj, JdbcStatement stmt) throws SQLException {
        stmt.setDttm(obj.dttm());
        stmt.setString(obj.token());
        stmt.setString(obj.username());
        stmt.setString(obj.email());
    }

    @Override
    public TokenStore.UserToken select(JdbcResult result) throws SQLException {
        return new TokenStore.UserToken(
                result.getDttm(),
                result.getString(),
                result.getString(),
                result.getString()
        );
    }
}
