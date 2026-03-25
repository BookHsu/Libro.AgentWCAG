# gh release download sample

```bash
gh release download v1.0.2 -R BookHsu/Libro.AgentWCAG -p 'libro-wcag-*-claude.zip'
unzip libro-wcag-*-claude.zip
python scripts/install-agent.py --agent claude
python scripts/doctor-agent.py --agent claude --verify-manifest-integrity
```
