using System.Collections.Generic;
using System.Threading;
using Avalonia_UI.Localization;
using Avalonia_UI.Services;

namespace Avalonia_UI.ViewModels;

public sealed record NodeSpecializedEditorContext
{
    public required WorkflowDefinitionNodeListItemViewModel Node { get; init; }

    public required IReadOnlyList<NodeConfigEditableFieldInputViewModel> Fields { get; init; }

    public required IReadOnlyList<WorkflowDefinitionConnectionListItemViewModel> Connections { get; init; }

    public required ISharedPublicationCatalogService CatalogService { get; init; }

    public ISqliteTableCatalogService? SqliteTableCatalogService { get; init; }

    public ISqliteDatabaseFileService? SqliteDatabaseFileService { get; init; }

    public required ILocalizationService LocalizationService { get; init; }

    public required CancellationToken LifetimeToken { get; init; }
}
