package clio.core.router;

import clio.core.router.VarArgParser;
import org.junit.Assert;
import org.junit.Test;

import java.util.Set;

public class TestVarArgParser {

    @Test
    public void testVarArgParser() {
        var parser = new VarArgParser();
        var result = parser.parse("--flag1 --option1 value1 value2  --optional_num 2.0 --flag2");
        Assert.assertEquals(true, result.get("flag1"));
        Assert.assertEquals(true, result.get("flag2").equals(true));
        Assert.assertEquals(Set.of("value1", "value2"), result.get("option1"));
        Assert.assertEquals(2.0, result.get("optional_num"));
    }
}
