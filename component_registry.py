import logging
from typing import Callable, Dict, Optional

from PySide6.QtCore import QObject

LOGGER = logging.getLogger(__name__)


class ComponentRegistry(QObject):

    def __init__(self):
        super().__init__()
        self.registry: Dict[str, dict] = {}

    def register_component(self, name: str, component_data: dict) -> None:
        """
        Enregistre un composant avec la structure attendue par App.

        Args:
            name: Nom du composant
            component_data: Structure complète avec definition et instances

        Raises:
            ValueError: Si le nom est vide ou si la structure est invalide
        """
        if not name or not isinstance(name, str):
            raise ValueError("Le nom du composant doit être une chaîne non vide")

        if not isinstance(component_data, dict):
            raise ValueError("Les données du composant doivent être un dictionnaire")

        # Validation de la structure des données
        self._validate_component_data(component_data)

        if name in self.registry:
            LOGGER.warning(f"Composant '{name}' déjà enregistré, remplacement...")

        self.registry[name] = component_data
        LOGGER.debug(f"Composant '{name}' enregistré avec succès")

    def _validate_component_data(self, component_data: dict) -> None:
        """
        Valide la structure des données d'un composant.

        Args:
            component_data: Données à valider

        Raises:
            ValueError: Si la structure est invalide
        """
        required_keys = {"definition", "instances"}
        if not all(key in component_data for key in required_keys):
            raise ValueError(f"La structure doit contenir les clés: {required_keys}")

        definition = component_data["definition"]
        if not isinstance(definition, dict):
            raise ValueError("'definition' doit être un dictionnaire")

        required_def_keys = {"class", "instantiation_policy", "instantiate_on"}
        if not all(key in definition for key in required_def_keys):
            raise ValueError(
                f"'definition' doit contenir les clés: {required_def_keys}"
            )

    def get_component_def(self, name: str) -> Optional[dict]:
        """
        Récupère la définition d'un composant.

        Args:
            name: Nom du composant

        Returns:
            Optional[dict]: Définition du composant ou None si non trouvé
        """
        component_data = self.registry.get(name)
        return component_data["definition"] if component_data else None

    def get_component_data(self, name: str) -> Optional[dict]:
        """
        Récupère les données complètes d'un composant (définition + instances).

        Args:
            name: Nom du composant

        Returns:
            Optional[dict]: Données complètes du composant ou None si non trouvé
        """
        return self.registry.get(name)

    def get_all_components(self) -> Dict[str, dict]:
        """
        Retourne une vue en lecture seule de tous les composants enregistrés.

        Note: Retourne une copie pour éviter les modifications externes.

        Returns:
            Dict[str, dict]: Vue du registre des composants
        """
        return dict(self.registry)

    def is_component_registered(self, name: str) -> bool:
        """
        Vérifie si un composant est enregistré.

        Args:
            name: Nom du composant à vérifier

        Returns:
            bool: True si le composant est enregistré
        """
        return name in self.registry

    def get_component_count(self) -> int:
        """
        Retourne le nombre de composants enregistrés.

        Returns:
            int: Nombre de composants dans le registre
        """
        return len(self.registry)

    def get_components_by_policy(self, policy: str) -> Dict[str, dict]:
        """
        Retourne tous les composants ayant une politique d'instanciation donnée.

        Args:
            policy: Politique d'instanciation ("singleton" ou "multi")

        Returns:
            Dict[str, dict]: Composants correspondant à la politique
        """
        return {
            name: component_data
            for name, component_data in self.registry.items()
            if component_data["definition"]["instantiation_policy"] == policy
        }

    def clear_registry(self) -> None:
        """
        Vide complètement le registre des composants.
        Utilisation recommandée uniquement pour les tests.
        """
        LOGGER.warning("Vidage complet du registre des composants")
        self.registry.clear()


# Décorateur pour enregistrer les composants
def register_app_component(
    name: str, policy: str = "singleton", instantiation_time: str = "setup"
) -> Callable:
    """
    Enregistre un composant dans le registre global.

    Args:
        name: Nom unique du composant
        policy: "singleton" | "multi" - Politique d'instanciation
        instantiation_time: "setup" | "demand" - Moment d'instanciation
    """
    # Validation des paramètres
    if policy not in ["singleton", "multi"]:
        raise ValueError(
            f"Policy '{policy}' invalide. Valeurs autorisées: singleton, multi"
        )

    if instantiation_time not in ["setup", "demand"]:
        raise ValueError(
            f"Instantiation time '{instantiation_time}' invalide. Valeurs autorisées: setup, demand"
        )

    def decorator(cls: type) -> type:
        # Structure corrigée pour correspondre aux attentes d'App
        APP_COMPONENT_REGISTRY.register_component(
            name,
            {
                "definition": {
                    "class": cls,
                    "instantiation_policy": policy,
                    "instantiate_on": instantiation_time,
                },
                "instances": {},
            },
        )
        return cls

    return decorator


# Instance globale du registre
APP_COMPONENT_REGISTRY = ComponentRegistry()
