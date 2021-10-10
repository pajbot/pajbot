from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional, Union

import importlib
import logging
import pkgutil
import re

from pajbot.migration.revision import Revision

if TYPE_CHECKING:
    from pajbot.bot import Bot
    from pajbot.migration.db import DatabaseMigratable
    from pajbot.migration.redis import RedisMigratable

MODULE_NAME_REGEX = re.compile(r"^(\d*)(?:\D(.+))?$")

log = logging.getLogger(__name__)


class Migration:
    def __init__(
        self,
        migratable: Union[DatabaseMigratable, RedisMigratable],
        revisions_package: Any,
        context: Bot,
    ):
        self.migratable = migratable
        self.revisions_package = revisions_package
        self.context = context

    def run(self, target_revision_id: Optional[int] = None) -> None:
        revisions = self.get_revisions()

        with self.migratable.create_resource() as resource:
            # NOTE: I don't know how to prove migratable is the same type from start to finish without adding a bunch of ugly ifs
            current_revision_id = self.migratable.get_current_revision(resource)  # type:ignore
        log.debug("migrate %s: current revision ID is %s", self.migratable.describe_resource(), current_revision_id)

        if current_revision_id is not None:
            revisions_to_run = [rev for rev in revisions if rev.id > current_revision_id]
        else:
            revisions_to_run = revisions

        # don't run all revisions, only up to the specified revision_id
        if target_revision_id is not None:
            revisions_to_run = [rev for rev in revisions_to_run if rev.id <= target_revision_id]

        log.debug("migrate %s: %s revisions to run", self.migratable.describe_resource(), len(revisions_to_run))

        for rev in revisions_to_run:
            # create a fresh resource for each individual migration
            # (we want to COMMIT after each successful migration revision)
            with self.migratable.create_resource() as resource:
                log.debug("migrate %s: running migration %s: %s", self.migratable.describe_resource(), rev.id, rev.name)
                rev.up_action(resource, self.context)
                # NOTE: I don't know how to prove migratable is the same type from start to finish without adding a bunch of ugly ifs
                self.migratable.set_revision(resource, rev.id)  # type:ignore

    def get_revisions(self) -> List[Revision]:
        package = self.revisions_package

        if isinstance(package, str):
            package = importlib.import_module(package)

        revisions: List[Revision] = []
        for importer, modname, ispkg in pkgutil.iter_modules(package.__path__):
            if ispkg:
                continue

            if isinstance(importer, importlib.abc.PathEntryFinder):
                maybe_module = importer.find_module(modname)
                if maybe_module is None:
                    continue
                module = maybe_module.load_module(modname)
                id_in_module = getattr(module, "ID", None)
                name_in_module = getattr(module, "NAME", None)
                up_action = getattr(module, "up", None)

                module_name_match = MODULE_NAME_REGEX.search(modname)

                id = None
                name = None

                if module_name_match is not None:
                    id_group = module_name_match.group(1)
                    if id_group is not None:
                        id = int(id_group)

                    name = module_name_match.group(2)

                if id_in_module is not None:
                    id = int(id_in_module)

                if name_in_module is not None:
                    name = str(name_in_module)

                if id is None:
                    raise ValueError(
                        f"Module {modname} does not specify ID= and its filename does not begin with a number. Cannot proceed."
                    )

                if name is None:
                    raise ValueError(
                        f"Module {modname} does not specify NAME= and its filename does not specify a name. Cannot proceed."
                    )

                if up_action is None:
                    raise ValueError(f"Module {modname} does not specify `def up()`. Cannot proceed.")

                if any(rev.id == id for rev in revisions):
                    raise ValueError(f"ID {id} was defined twice. Cannot proceed.")

                revision = Revision(id, name, up_action)

                revisions.append(revision)
            elif isinstance(importer, importlib.abc.MetaPathFinder):
                log.info(f"Not sure how to handle metapathfinder {importer}, {type(importer)}")

        if len(revisions) <= 0:
            raise ValueError(f"No revisions found under {package.__path__}.")

        revisions.sort(key=lambda rev: rev.id)

        return revisions
