"""Armazenamentos de arquivos estáticos usados pelo ERP."""

from whitenoise.storage import CompressedManifestStaticFilesStorage


class JazzminCompatibleStaticFilesStorage(CompressedManifestStaticFilesStorage):
    """Preserva hashes e permite ao Jazzmin referenciar o diretório de temas."""

    jazzmin_theme_base = "vendor/bootswatch"

    def url(self, name, force=False):
        normalized_name = name.rstrip("/")
        if normalized_name == self.jazzmin_theme_base:
            return f"{self.base_url.rstrip('/')}/{normalized_name}"
        return super().url(name, force=force)
