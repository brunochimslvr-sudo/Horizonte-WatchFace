import javax.xml.XMLConstants;
import javax.xml.transform.stream.StreamSource;
import javax.xml.validation.*;
import java.io.File;

public class Validate {
    public static void main(String[] a) throws Exception {
        SchemaFactory f = SchemaFactory.newInstance(XMLConstants.W3C_XML_SCHEMA_NS_URI);
        Schema s = f.newSchema(new File(a[0]));
        s.newValidator().validate(new StreamSource(new File(a[1])));
        System.out.println("XML valido contra o schema WFF");
    }
}
