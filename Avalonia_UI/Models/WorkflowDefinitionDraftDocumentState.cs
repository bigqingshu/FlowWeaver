using System;

namespace Avalonia_UI.Models;

public sealed class WorkflowDefinitionDraftDocumentState
{
    public string OriginalDefinitionJson { get; private set; } = string.Empty;

    public void AcceptOriginalDefinition(string definitionJson)
    {
        OriginalDefinitionJson = definitionJson;
    }

    public bool IsDirty(string draftJson)
    {
        return !string.Equals(
            draftJson,
            OriginalDefinitionJson,
            StringComparison.Ordinal);
    }
}
