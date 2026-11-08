from dataclasses import dataclass, field, asdict


@dataclass
class RegistroCVE:
    """
    Lo que se guarda de cada CVE de la NVD. La respuesta de la API trae mucho más,
    pero para indexar alcanza con esto y el archivo queda bastante más chico.

    Los CPE no se guardan como texto (no se usan como entrada del buscador),
    solo se marca si existían, para poder separar los resultados después.
    """

    id: str
    publicada: str
    estado: str
    emisor: str
    descripcion: str
    productos: list[str] = field(default_factory=list)
    referencias: list[str] = field(default_factory=list)
    tiene_cpe_nvd: bool = False
    tiene_cpe_cna: bool = False

    @classmethod
    def desde_nvd(cls, cve: dict) -> "RegistroCVE":
        descripcion = ""
        for d in cve.get("descriptions", []):
            if d.get("lang") == "en":
                descripcion = d.get("value", "")
                break

        # productos que declara quien emite la CVE (bloque "affected"), sin normalizar
        productos = []
        tiene_cpe_cna = False
        for bloque in cve.get("affected", []):
            for dato in bloque.get("affectedData", []):
                vendor = dato.get("vendor", "").strip()
                product = dato.get("product", "").strip()
                nombre = f"{vendor} {product}".strip()
                if nombre and nombre not in productos:
                    productos.append(nombre)
                if dato.get("cpes"):
                    tiene_cpe_cna = True

        referencias = [r["url"] for r in cve.get("references", []) if "url" in r]

        return cls(
            id=cve["id"],
            publicada=cve.get("published", ""),
            estado=cve.get("vulnStatus", ""),
            emisor=cve.get("sourceIdentifier", ""),
            descripcion=descripcion,
            productos=productos,
            referencias=referencias,
            tiene_cpe_nvd=bool(cve.get("configurations")),
            tiene_cpe_cna=tiene_cpe_cna,
        )

    @classmethod
    def desde_dict(cls, d: dict) -> "RegistroCVE":
        return cls(**d)

    def a_dict(self) -> dict:
        return asdict(self)

    def esta_rechazada(self) -> bool:
        return self.estado == "Rejected"
