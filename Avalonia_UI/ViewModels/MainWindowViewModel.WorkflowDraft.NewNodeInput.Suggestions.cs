using System;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool ShouldApplySuggestedNewDraftNodeInstanceId()
    {
        return string.IsNullOrWhiteSpace(NewDraftNodeInstanceId)
            || string.Equals(
                NewDraftNodeInstanceId,
                lastSuggestedNewDraftNodeInstanceId,
                StringComparison.Ordinal);
    }

    private bool ShouldApplySuggestedNewDraftNodeConfigJson()
    {
        return string.IsNullOrWhiteSpace(NewDraftNodeConfigJson)
            || string.Equals(NewDraftNodeConfigJson.Trim(), "{}", StringComparison.Ordinal)
            || string.Equals(
                NewDraftNodeConfigJson,
                lastSuggestedNewDraftNodeConfigJson,
                StringComparison.Ordinal);
    }
}
