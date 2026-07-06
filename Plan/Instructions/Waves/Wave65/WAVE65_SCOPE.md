# Wave65 Scope - Exhaustive AI Source Coverage Closure

Wave65 is active when the session needs confidence that Plan/Items and Plan/Tracker directly cover every current Plan file.

Hard rules:
- Every current Plan file must be represented by existing baseline Items/Tracker coverage or a Wave65 closure row.
- Every closure row must include Citation_File, Citation_Full_Path, Citation_Section, Citation_Line_Start, Citation_Line_End, Citation_Excerpt, Source_Key, and Source_File_Relative.
- Human_Input_Allowed and Human_Work_Allowed must be FALSE.
- The autonomous session must rerun the Wave65 generator after adding or renaming any Plan file.
- Localized image, video, GIF, mask, prompt, frame, or audio work cannot pass if the whole generated artifact has unrelated defects.
