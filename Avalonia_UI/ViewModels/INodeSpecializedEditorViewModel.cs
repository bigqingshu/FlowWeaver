using System;

namespace Avalonia_UI.ViewModels;

public interface INodeSpecializedEditorViewModel : IDisposable
{
    string NodeType { get; }

    bool TryPrepareApply(out string errorMessage);

    void RefreshLocalizedText();
}
