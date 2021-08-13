from collections import Counter
import base64
import hashlib
import inspect
import os


class ResourceConfig(object):
    """Config singleton for web resources.
    """

    def __init__(self):
        self.development = False


config = ResourceConfig()


class ResourceMixin(object):
    """Mixin for ``Resource`` and ``ResourceGroup``.
    """

    def __init__(self, name='', path='', include=True):
        self.name = name
        self.path = path
        self.include = include
        self.resolved_path = ''

    @property
    def include(self):
        if callable(self._include):
            return self._include()
        return self._include

    @include.setter
    def include(self, include):
        self._include = include

    @property
    def resolved_path(self):
        if self._resolved_path:
            return self._resolved_path
        return self.path

    @resolved_path.setter
    def resolved_path(self, path):
        self._resolved_path = path


class ResourceError(ValueError):
    """Resource related exception.
    """


class Resource(ResourceMixin):
    """A web resource.
    """
    _hash_algorithms = dict(
        sha256=hashlib.sha256,
        sha384=hashlib.sha384,
        sha512=hashlib.sha512
    )

    def __init__(self, name='', depends='', directory=None, path='',
                 resource=None, compressed=None, include=True, hash_=False,
                 hash_algorithm='sha384', group=None, url=None,
                 crossorigin=None, referrerpolicy=None, type_=None):
        """Base class for resources.

        :param name: The resource unique name.
        :param depends: Optional name of dependency resource.
        :param directory: Directory containing the resource files.
        :param path: URL path for HTML tag link creation.
        :param resource: Resource file.
        :param compressed: Optional compressed version of resource file.
        :param include: Flag or callback function returning a flag whether to
            include the resource.
        :param hash_: Flag whether to render resource URL with hash. Has no
            effect if ``url`` is given.
        :param hash_algorithm: Name of the hashing algorithm. Either 'sha256',
            'sha384' or 'sha512'. Defaults to 'sha384'.
        :param group: Optional resource group instance.
        :param url: Optional resource URL to use for external resources.
        :param crossorigin: Sets the mode of the request to an HTTP CORS Request.
        :param referrerpolicy: Specifies which referrer information to send when
            fetching the resource.
        :param type_: Specifies the media type of the resource.
        :raise ResourceError: No resource and no url given.
        """
        if resource is None and url is None:
            raise ResourceError('Either resource or url must be given')
        super(Resource, self).__init__(name=name, path=path, include=include)
        self.depends = depends
        self.directory = directory
        self.resource = resource
        self.compressed = compressed
        self.hash_ = hash_
        self.hash_algorithm = hash_algorithm
        if group:
            group.add(self)
        self.url = url
        self.crossorigin = crossorigin
        self.referrerpolicy = referrerpolicy
        self.type_ = type_

    @property
    def directory(self):
        return self._directory

    @directory.setter
    def directory(self, directory):
        if not directory:
            directory = self._module_directory()
        elif directory.startswith('.'):
            directory = os.path.join(self._module_directory(), directory)
        self._directory = os.path.abspath(directory)

    @property
    def file_name(self):
        """Resource file name depending on operation mode.
        """
        if not config.development and self.compressed:
            return self.compressed
        return self.resource

    @property
    def file_path(self):
        """Absolute resource file path depending on operation mode.
        """
        return os.path.join(self.directory, self.file_name)

    @property
    def file_data(self):
        """File content of resource depending on operation mode.
        """
        with open(self.file_path, 'rb') as f:
            return f.read()

    @property
    def file_hash(self):
        """Hash of resource file content.
        """
        if not config.development and hasattr(self, '_file_hash'):
            return self._file_hash
        hash_func = self._hash_algorithms[self.hash_algorithm]
        hash_ = base64.b64encode(hash_func(self.file_data).digest()).decode()
        self._file_hash = hash_
        return hash_

    def resource_url(self, base_url):
        """Create URL for resource.

        :param base_url: The base URL to create the URL resource.
        """
        if self.url is not None:
            return self.url
        path = self.resolved_path.strip('/')
        if path:
            parts = [base_url.strip('/'), path, self.file_name]
        else:
            parts = [base_url.strip('/'), self.file_name]
        url = u'/'.join(parts)
        if self.hash_:
            url = u'{}#{}'.format(url, self.file_hash)
        return url

    def render(self, base_url):
        """Renders the resource HTML tag. must be implemented on subclass.

        :param base_url: The base URL to create the URL resource.
        :raise NotImplementedError: Method is abstract.
        """
        raise NotImplementedError('Abstract resource not implements ``render``')

    def _render_tag(self, tag, closing_tag, **attrs):
        attrs_ = list()
        for name, val in attrs.items():
            if val is None:
                continue
            attrs_.append(u'{0}="{1}"'.format(name, val))
        attrs_ = u' {0}'.format(u' '.join(sorted(attrs_)))
        if not closing_tag:
            return u'<{tag}{attrs} />'.format(tag=tag, attrs=attrs_)
        return u'<{tag}{attrs}></{tag}>'.format(tag=tag, attrs=attrs_)

    def _module_directory(self):
        module = inspect.getmodule(inspect.currentframe().f_back)
        return os.path.dirname(os.path.abspath(module.__file__))

    def __repr__(self):
        return (
            '<{} name="{}", depends="{}">'
        ).format(
            self.__class__.__name__,
            self.name,
            self.depends
        )


class ScriptResource(Resource):
    """A Javascript resource.
    """

    def __init__(self, name='', depends='', directory=None, path='',
                 resource=None, compressed=None, include=True, hash_=False,
                 hash_algorithm='sha384', group=None, url=None,
                 crossorigin=None, referrerpolicy=None, type_=None,
                 async_=None, defer=None, integrity=None, nomodule=None):
        """Create script resource.

        :param name: The resource unique name.
        :param depends: Optional name of dependency resource.
        :param directory: Directory containing the resource files.
        :param path: URL path for HTML tag link creation.
        :param resource: Resource file.
        :param compressed: Optional compressed version of resource file.
        :param include: Flag or callback function returning a flag whether to
            include the resource.
        :param hash_: Flag whether to render resource URL with hash. Has no
            effect if ``url`` is given.
        :param hash_algorithm: Name of the hashing algorithm. Either 'sha256',
            'sha384' or 'sha512'. Defaults to 'sha384'.
        :param group: Optional resource group instance.
        :param url: Optional resource URL to use for external resources.
        :param crossorigin: Sets the mode of the request to an HTTP CORS Request.
        :param referrerpolicy: Specifies which referrer information to send when
            fetching the resource.
        :param type_: Specifies the media type of the resource.
        :param async_: Specifies that the script is executed asynchronously
            (only for external scripts)
        :param defer: Specifies that the script is executed when the page has
            finished parsing (only for external scripts).
        :param integrity: Allows a browser to check the fetched script to ensure
            that the code is never loaded if the source has been manipulated.
        :param nomodule: Specifies that the script should not be executed in
            browsers supporting ES2015 modules.
        :raise ResourceError: No resource and no url given.
        """
        super(ScriptResource, self).__init__(
            name=name, depends=depends, directory=directory, path=path,
            resource=resource, compressed=compressed, include=include,
            hash_=hash_, hash_algorithm=hash_algorithm, group=group, url=url,
            crossorigin=crossorigin, referrerpolicy=referrerpolicy, type_=type_
        )
        self.async_ = async_
        self.defer = defer
        self.integrity = integrity
        self.nomodule = nomodule

    def render(self, base_url):
        """Renders the resource HTML ``script`` tag.

        :param base_url: The base URL to create the URL resource.
        """
        return self._render_tag('script', True, **{
            'src': self.resource_url(base_url),
            'crossorigin': self.crossorigin,
            'referrerpolicy': self.referrerpolicy,
            'type': self.type_,
            'async': self.async_,
            'defer': self.defer,
            'integrity': self.integrity,
            'nomodule': self.nomodule
        })


class LinkResource(Resource):
    """A Link Resource.
    """

    def __init__(self, name='', depends='', directory=None, path='',
                 resource=None, compressed=None, include=True, hash_=False,
                 hash_algorithm='sha384', group=None, url=None,
                 crossorigin=None, referrerpolicy=None, type_=None,
                 hreflang=None, media=None, rel=None, sizes=None, title=None):
        """Create link resource.

        :param name: The resource unique name.
        :param depends: Optional name of dependency resource.
        :param directory: Directory containing the resource files.
        :param path: URL path for HTML tag link creation.
        :param resource: Resource file.
        :param compressed: Optional compressed version of resource file.
        :param include: Flag or callback function returning a flag whether to
            include the resource.
        :param hash_: Flag whether to render resource URL with hash. Has no
            effect if ``url`` is given.
        :param hash_algorithm: Name of the hashing algorithm. Either 'sha256',
            'sha384' or 'sha512'. Defaults to 'sha384'.
        :param group: Optional resource group instance.
        :param url: Optional resource URL to use for external resources.
        :param crossorigin: Sets the mode of the request to an HTTP CORS Request.
        :param referrerpolicy: Specifies which referrer information to send when
            fetching the resource.
        :param type_: Specifies the media type of the resource.
        :param hreflang: Specifies the language of the text in the linked
            document.
        :param media: Specifies on what device the linked document will be
            displayed.
        :param rel: Required. Specifies the relationship between the current
            document and the linked document.
        :param sizes: Specifies the size of the linked resource. Only for
            rel="icon".
        :param title: Defines a preferred or an alternate stylesheet.
        :raise ResourceError: No resource and no url given.
        """
        super(LinkResource, self).__init__(
            name=name, depends=depends, directory=directory, path=path,
            resource=resource, compressed=compressed, include=include,
            hash_=hash_, hash_algorithm=hash_algorithm, group=group, url=url,
            crossorigin=crossorigin, referrerpolicy=referrerpolicy, type_=type_
        )
        self.hreflang = hreflang
        self.media = media
        self.rel = rel
        self.sizes = sizes
        self.title = title

    def render(self, base_url):
        """Renders the resource HTML ``link`` tag.

        :param base_url: The base URL to create the URL resource.
        """
        return self._render_tag('link', False, **{
            'href': self.resource_url(base_url),
            'crossorigin': self.crossorigin,
            'referrerpolicy': self.referrerpolicy,
            'type': self.type_,
            'hreflang': self.hreflang,
            'media': self.media,
            'rel': self.rel,
            'sizes': self.sizes,
            'title': self.title
        })


class StyleResource(LinkResource):
    """A Stylesheet Resource.
    """

    def __init__(self, name='', depends='', directory=None, path='',
                 resource=None, compressed=None, include=True, hash_=False,
                 hash_algorithm='sha384', group=None, url=None,
                 crossorigin=None, referrerpolicy=None, hreflang=None,
                 media='all', rel='stylesheet', sizes=None, title=None):
        """Create link resource.

        :param name: The resource unique name.
        :param depends: Optional name of dependency resource.
        :param directory: Directory containing the resource files.
        :param path: URL path for HTML tag link creation.
        :param resource: Resource file.
        :param compressed: Optional compressed version of resource file.
        :param include: Flag or callback function returning a flag whether to
            include the resource.
        :param hash_: Flag whether to render resource URL with hash. Has no
            effect if ``url`` is given.
        :param hash_algorithm: Name of the hashing algorithm. Either 'sha256',
            'sha384' or 'sha512'. Defaults to 'sha384'.
        :param group: Optional resource group instance.
        :param url: Optional resource URL to use for external resources.
        :param crossorigin: Sets the mode of the request to an HTTP CORS Request.
        :param referrerpolicy: Specifies which referrer information to send when
            fetching the resource.
        :param hreflang: Specifies the language of the text in the linked
            document.
        :param media: Specifies on what device the linked document will be
            displayed. Defaults to "all".
        :param rel: Specifies the relationship between the current document and
            the linked document. Defaults to "stylesheet".
        :param title: Defines a preferred or an alternate stylesheet.
        :raise ResourceError: No resource and no url given.
        """
        super(StyleResource, self).__init__(
            name=name, depends=depends, directory=directory, path=path,
            resource=resource, compressed=compressed, include=include,
            hash_=hash_, hash_algorithm=hash_algorithm, group=group, url=url,
            crossorigin=crossorigin, referrerpolicy=referrerpolicy,
            type_='text/css', hreflang=hreflang, media=media, rel=rel,
            sizes=None, title=title
        )


class ResourceGroup(ResourceMixin):
    """A resource group.
    """

    def __init__(self, name='', path='', include=True, group=None):
        """Create resource group.

        :param name: The resource group name.
        :param path: Optional URL path for HTML tag link creation. Takes
            precedence over group members paths.
        :param include: Flag or callback function returning a flag whether to
            include the resource group.
        :param group: Optional resource group instance.
        """
        super(ResourceGroup, self).__init__(name=name, path=path, include=include)
        if group:
            group.add(self)
        self._members = []

    @property
    def members(self):
        """List of group members."""
        return self._members

    def add(self, member):
        """Add member to resource group.

        :param member: Either ``ResourceGroup`` or ``Resource`` instance.
        :raise ResourceError: Invalid member given.
        """
        if not isinstance(member, (ResourceGroup, Resource)):
            raise ResourceError(
                'Resource group can only contain instances '
                'of ``ResourceGroup`` or ``Resource``'
            )
        self._members.append(member)

    def __repr__(self):
        return '<{} name="{}">'.format(
            self.__class__.__name__,
            self.name
        )


class ResourceConflictError(ResourceError):
    """Multiple resources declared with the same name.
    """

    def __init__(self, counter):
        conflicting = list()
        for name, count in counter.items():
            if count > 1:
                conflicting.append(name)
        msg = 'Conflicting resource names: {}'.format(conflicting)
        super(ResourceConflictError, self).__init__(msg)


class ResourceCircularDependencyError(ResourceError):
    """Resources define circular dependencies.
    """

    def __init__(self, resources):
        msg = 'Resources define circular dependencies: {}'.format(resources)
        super(ResourceCircularDependencyError, self).__init__(msg)


class ResourceMissingDependencyError(ResourceError):
    """Resource depends on a missing resource.
    """

    def __init__(self, resources):
        msg = 'Resource define missing dependency: {}'.format(resources)
        super(ResourceMissingDependencyError, self).__init__(msg)


class ResourceResolver(object):
    """Resource resolver.
    """

    def __init__(self, members):
        """Create resource resolver.

        :param members: Either single or list of ``Resource`` or
            ``ResourceGroup`` instances.
        :raise ResourceError: Members contain invalid member.
        """
        if not isinstance(members, (list, tuple)):
            members = [members]
        for member in members:
            if not isinstance(member, (Resource, ResourceGroup)):
                raise ResourceError(
                    'members can only contain instances '
                    'of ``ResourceGroup`` or ``Resource``'
                )
        self.members = members

    def _resolve_paths(self, members=None, path=''):
        if members is None:
            members = self.members
        for member in members:
            if path:
                member.resolved_path = path
            if isinstance(member, ResourceGroup):
                self._resolve_paths(
                    members=member.members,
                    path=member.resolved_path
                )

    def _flat_resources(self, members=None):
        if members is None:
            members = self.members
        resources = []
        for member in members:
            if not member.include:
                continue
            if isinstance(member, ResourceGroup):
                resources += self._flat_resources(members=member.members)
            else:
                resources.append(member)
        return resources

    def resolve(self):
        """Return all resources from members as flat list ordered by
        dependencies.

        :raise ResourceConflictError: Resource list contains conflicting names
        :raise ResourceMissingDependencyError: Dependency resource not included
        :raise ResourceCircularDependencyError: Circular dependency defined.
        """
        self._resolve_paths()
        resources = self._flat_resources()
        names = [res.name for res in resources]
        counter = Counter(names)
        if len(resources) != len(counter):
            raise ResourceConflictError(counter)
        ret = []
        handled = {}
        for resource in resources[:]:
            if not resource.depends:
                ret.append(resource)
                handled[resource.name] = resource
                resources.remove(resource)
            elif resource.depends not in names:
                raise ResourceMissingDependencyError(resource)
        count = len(resources)
        while count > 0:
            count -= 1
            for resource in resources[:]:
                if resource.depends in handled:
                    dependency = handled[resource.depends]
                    index = ret.index(dependency)
                    ret.insert(index + 1, resource)
                    handled[resource.name] = resource
                    resources.remove(resource)
                    break
        if resources:
            raise ResourceCircularDependencyError(resources)
        return ret


class ResourceRenderer(object):
    """Resource renderer.
    """

    def __init__(self, resolver, base_url='https://tld.org'):
        """Create resource renderer.

        :param resolver: ``ResourceResolver`` instance.
        :param base_url: Base URL to render resource HTML tags.
        """
        self.resolver = resolver
        self.base_url = base_url

    def render(self):
        """Render resources.
        """
        return u'\n'.join([
            res.render(self.base_url) for res in self.resolver.resolve()
        ])
